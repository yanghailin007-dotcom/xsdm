"""
Nano Banana文生图API客户端
支持文本生成图像功能，用于角色生成
"""
import os
import sys
import requests
import json
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
from urllib.parse import quote

# 🔥 图像处理导入
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.utils.logger import get_logger, Logger, LogLevel

# 🔥 配置日志系统：将所有可能的输出重定向到文件，避免控制台被base64数据填满
def _setup_global_logging():
    """在模块级别配置日志系统"""
    import logging as python_logging
    
    # 创建日志目录
    log_dir = BASE_DIR / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / 'nanobanana_detailed.log'
    
    # 创建Python标准日志的文件处理器
    file_handler = python_logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(python_logging.DEBUG)
    formatter = python_logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(formatter)
    
    # 捕获所有可能打印base64数据的logger
    loggers_to_capture = [
        'requests', 'urllib3', 'requests.packages', 'requests.packages.urllib3',
        'urllib3.connectionpool', 'urllib3.util', 'urllib3.util.retry',
        'httpx', 'httpcore', 'http.client'
    ]
    
    for logger_name in loggers_to_capture:
        logger = python_logging.getLogger(logger_name)
        logger.setLevel(python_logging.DEBUG)
        # 清除所有现有的handlers
        logger.handlers.clear()
        # 只添加文件处理器
        logger.addHandler(file_handler)
        # 阻止传播到父logger（避免输出到控制台）
        logger.propagate = False
    
    # 同时启用我们的自定义日志系统的文件日志
    Logger.enable_file_logging(str(log_file))
    # 将控制台日志级别设置为INFO，只显示重要信息
    Logger.set_global_level(LogLevel.INFO)
    
    return log_file

# 在模块加载时配置日志
_log_file = _setup_global_logging()


class NanoBananaImageGenerator:
    """Nano Banana文生图API客户端（用于角色生成）"""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化Nano Banana文生图客户端

        Args:
            api_key: API密钥，如果为None则从配置获取
            base_url: API基础URL，如果为None则从配置获取
        """
        self.logger = get_logger("NanoBananaImageGenerator")
        self.logger.info(f"📝 详细日志已启用，文件位置: {_log_file}")

        # 从配置导入或使用传入的参数
        try:
            from config.config import CONFIG
            config = CONFIG.get('nanobanana', {})

            # 🔥 多供应商配置
            self.providers = config.get('providers', [
                {
                    'name': 'xiaochuang',
                    'base_url': 'http://intoai.xiaochuang.cc/v1beta/models/gemini-3-pro-image-preview:generateContent',
                    'api_key': config.get('api_key', ''),
                    'enabled': True
                },
                {
                    'name': 'ai-wx',
                    'base_url': 'https://jyapi.ai-wx.cn/v1/images/generations',
                    'model': 'gemini-3-pro-image-preview-1K',
                    'api_key': config.get('api_key_aiwx', config.get('api_key', '')),  # 可以使用相同或不同的key
                    'enabled': True
                }
            ])

            # 兼容旧配置：如果传入了base_url或api_key，使用第一个provider
            if base_url or api_key:
                self.providers[0]['base_url'] = base_url or self.providers[0]['base_url']
                self.providers[0]['api_key'] = api_key or self.providers[0]['api_key']

            self.base_url = self.providers[0]['base_url']  # 保持向后兼容
            self.api_key = self.providers[0]['api_key']  # 保持向后兼容

            # 🔥 增加默认超时时间，特别是处理包含参考图像的请求
            default_timeout = config.get('timeout', 60)
            self.timeout_without_ref = default_timeout  # 无参考图像时的超时
            self.timeout_with_ref = max(default_timeout * 3, 300)  # 有参考图像时超时3倍或至少300秒
            self.timeout = default_timeout
            self.max_retries = config.get('max_retries', 3)
            self.enabled = config.get('enabled', True)

            self.default_config = config.get('default_config', {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": {
                    "aspectRatio": "16:9",
                    "imageSize": "4K"
                }
            })

        except ImportError:
            # 如果配置导入失败，使用默认值（不从环境变量读取）
            self.providers = [
                {
                    'name': 'xiaochuang',
                    'base_url': 'http://intoai.xiaochuang.cc/v1beta/models/gemini-3-pro-image-preview:generateContent',
                    'api_key': api_key or '',
                    'enabled': True
                },
                {
                    'name': 'ai-wx',
                    'base_url': 'https://jyapi.ai-wx.cn/v1/images/generations',
                    'model': 'gemini-3-pro-image-preview-1K',
                    'api_key': api_key or '',
                    'enabled': True
                }
            ]
            self.base_url = base_url or self.providers[0]['base_url']
            self.api_key = api_key or ''  # 不再从环境变量读取
            self.timeout = 60
            self.max_retries = 3
            self.enabled = True
            self.default_config = {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": {
                    "aspectRatio": "16:9",
                    "imageSize": "4K"
                }
            }
        
        # 验证API密钥
        if not self.api_key:
            self.logger.warning("⚠️ 未配置Nano Banana API密钥，请在config/config.py中配置nanobanana.api_key")
        else:
            # API密钥已配置，无需打印详细信息
            pass
        
        # 确保输出目录存在
        self.output_dir = BASE_DIR / 'generated_images'
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.debug(f"✅ Nano Banana客户端初始化完成 (enabled={self.enabled})")
        self.logger.info(f"🔧 已配置 {len(self.providers)} 个图像生成供应商")
        for idx, provider in enumerate(self.providers):
            status = "✅ 启用" if provider.get('enabled', True) else "❌ 禁用"
            self.logger.info(f"  供应商{idx+1}: {provider['name']} - {status}")

    def _call_provider_api(
        self,
        provider: Dict[str, Any],
        prompt: str,
        aspect_ratio: str,
        image_size: str,
        all_reference_images: List[str],
        parts: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        调用单个供应商的API

        Args:
            provider: 供应商配置
            prompt: 提示词
            aspect_ratio: 图片比例
            image_size: 图片尺寸
            all_reference_images: 参考图像列表
            parts: 请求parts（包含文本和图像）

        Returns:
            dict: API响应结果
        """
        provider_name = provider.get('name', 'unknown')
        base_url = provider['base_url']
        api_key = provider['api_key']

        self.logger.info(f"🔌 使用供应商: {provider_name}")
        self.logger.info(f"  - API URL: {base_url}")

        # 根据供应商类型构建不同的请求体
        if provider_name == 'ai-wx':
            # AI-WX 使用 OpenAI 兼容格式
            request_body = {
                "model": provider.get('model', 'gemini-3-pro-image-preview-1K'),
                "prompt": prompt,
                "size": f"{image_size.lower()}",  # 1k, 2k, 4k
                "aspect_ratio": aspect_ratio,
                "n": 1
            }
        else:
            # 默认使用 Gemini 格式
            request_body = {
                "contents": [
                    {
                        "parts": parts
                    }
                ],
                "generationConfig": {
                    "responseModalities": ["TEXT", "IMAGE"],
                    "imageConfig": {
                        "aspectRatio": aspect_ratio,
                        "imageSize": image_size
                    }
                }
            }

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

        self.logger.info(f"🚀 发送POST请求到 {provider_name} API...")

        response = requests.post(
            base_url,
            json=request_body,
            headers=headers,
            timeout=self.timeout
        )

        self.logger.info(f"📥 收到 {provider_name} API响应:")
        self.logger.info(f"  - 状态码: {response.status_code}")
        self.logger.info(f"  - 响应大小: {len(response.content)} 字节")

        return {
            'response': response,
            'provider_name': provider_name
        }

    def generate_image(
        self,
        prompt: str,
        aspect_ratio: str = "16:9",
        image_size: str = "4K",
        save_path: Optional[str] = None,
        retry_count: int = 0,
        reference_image: Optional[str] = None,
        reference_images: Optional[List[str]] = None,
        provider_index: int = 0
    ) -> Dict[str, Any]:
        """
        生成图像（支持多供应商自动切换）

        Args:
            prompt: 提示词描述
            aspect_ratio: 图片比例 (16:9, 4:3, 1:1, 9:16)
            image_size: 图片尺寸 (1K, 2K, 4K)
            save_path: 保存路径，如果为None则自动生成
            retry_count: 当前重试次数
            reference_image: 参考图像路径（单张，兼容旧版本）
            reference_images: 参考图像路径列表（多张，最多5张，优先使用）
            provider_index: 当前使用的供应商索引

        Returns:
            dict: 包含生成结果的字典
        """
        if not self.enabled:
            return {
                "success": False,
                "error": "Nano Banana服务未启用"
            }
        
        if not self.api_key:
            return {
                "success": False,
                "error": "未配置API密钥，请在config/config.py中配置nanobanana.api_key"
            }
        
        # 🔥 新增：处理参考图像（支持多个参考图像，最多5张）
        # 🔥 集成图像压缩功能，避免请求体过大导致连接被服务器断开
        parts = []
        
        # 🔥 重要：先添加文本提示词，再添加参考图像（符合API规范）
        parts.append({
            "text": prompt
        })
        
        # 🔥 合并参考图像：优先使用 reference_images（数组），否则使用 reference_image（单张）
        all_reference_images = []
        if reference_images:
            # 新版本：使用多张参考图像
            all_reference_images = reference_images[:5]  # 最多5张
        elif reference_image:
            # 兼容旧版本：使用单张参考图像
            all_reference_images = [reference_image]
        
        # 添加所有参考图像到parts（先压缩）
        if all_reference_images:
            import mimetypes
            # 🔥 导入图像压缩工具
            try:
                from src.utils.image_compressor import compress_image, MAX_IMAGE_SIZE_BYTES
                # 限制单张参考图像最大1.5MB（比默认2MB更保守，避免多张图时超过限制）
                max_size_mb = 1.5
                self.logger.info(f"🗜️  参考图像压缩模式已启用，单张限制: {max_size_mb} MB")
            except ImportError:
                compress_image = None
                max_size_mb = None
                self.logger.warning("⚠️  图像压缩工具未找到，将使用原始图像")
            
            for idx, ref_path in enumerate(all_reference_images):
                try:
                    # 读取并编码参考图像
                    if not os.path.exists(ref_path):
                        self.logger.warning(f"⚠️ 参考图像{idx+1}不存在: {ref_path}")
                        continue
                    
                    with open(ref_path, 'rb') as f:
                        ref_image_data = f.read()
                    
                    original_size = len(ref_image_data)
                    self.logger.debug(f"📸 参考图{idx+1}原始大小: {original_size / (1024*1024):.2f} MB")
                    
                    # 🔥 如果压缩工具可用，先压缩图像
                    if compress_image and max_size_mb:
                        try:
                            # 将图像数据转换为base64 data URL格式
                            raw_base64 = base64.b64encode(ref_image_data).decode('utf-8')
                            data_url = f"data:image/jpeg;base64,{raw_base64}"
                            
                            # 压缩图像
                            compressed_data_url = compress_image(
                                data_url,
                                max_size_mb=max_size_mb,
                                quality=85,
                                max_dimension=1280  # 限制最大尺寸为1280px
                            )
                            
                            # 提取压缩后的base64数据
                            if ',' in compressed_data_url:
                                compressed_base64 = compressed_data_url.split(',', 1)[1]
                            else:
                                compressed_base64 = compressed_data_url
                            
                            ref_image_base64 = compressed_base64
                            compressed_size = len(base64.b64decode(compressed_base64))
                            compression_ratio = (1 - compressed_size / original_size) * 100
                            self.logger.info(f"🗜️  参考图{idx+1}压缩: {original_size / (1024*1024):.2f} MB -> "
                                           f"{compressed_size / (1024*1024):.2f} MB (压缩率: {compression_ratio:.1f}%)")
                        except Exception as compress_error:
                            self.logger.warning(f"⚠️  参考图{idx+1}压缩失败，使用原始数据: {compress_error}")
                            ref_image_base64 = base64.b64encode(ref_image_data).decode('utf-8')
                    else:
                        # 不压缩，直接使用原始数据
                        ref_image_base64 = base64.b64encode(ref_image_data).decode('utf-8')
                    
                    # 获取MIME类型
                    mime_type = mimetypes.guess_type(ref_path)[0] or 'image/jpeg'
                    
                    parts.append({
                        "inline_data": {  # 使用下划线格式，符合API规范
                            "mime_type": mime_type,  # 使用下划线格式
                            "data": ref_image_base64
                        }
                    })
                    self.logger.debug(f"✅ 已添加参考图像{idx+1}: {ref_path}")
                except Exception as e:
                    self.logger.debug(f"⚠️ 添加参考图像{idx+1}失败: {e}")
            
            self.logger.info(f"🖼️ 共添加 {len([p for p in parts if 'inline_data' in p])} 张参考图像（已压缩）")
        
        # 构建请求体（移除role字段，使用简化的contents结构）
        request_body = {
            "contents": [
                {
                    "parts": parts
                }
            ],
            "generationConfig": {
                "responseModalities": ["TEXT", "IMAGE"],
                "imageConfig": {
                    "aspectRatio": aspect_ratio,
                    "imageSize": image_size
                }
            }
        }
        
        try:
            self.logger.info(f"🎨 开始生成图像")
            self.logger.info(f"📋 请求配置:")
            self.logger.info(f"  - 比例: {aspect_ratio}")
            self.logger.info(f"  - 尺寸: {image_size}")
            self.logger.info(f"  - 超时: {self.timeout}秒")
            self.logger.info(f"  - 提示词长度: {len(prompt)} 字符")
            self.logger.info(f"  - 提示词内容: {prompt}")  # 显示完整提示词

            # 🔥 显示参考图像信息
            if all_reference_images:
                self.logger.info(f"  - 参考图像数量: {len(all_reference_images)} 张")
                for idx, ref_path in enumerate(all_reference_images):
                    self.logger.info(f"    参考图{idx+1}: {ref_path}")

            # 🔥 多供应商自动切换逻辑
            last_error = None
            response = None
            provider_name = None

            for attempt_idx in range(provider_index, len(self.providers)):
                provider = self.providers[attempt_idx]

                # 跳过禁用的供应商
                if not provider.get('enabled', True):
                    self.logger.info(f"⏭️  跳过禁用的供应商: {provider.get('name', 'unknown')}")
                    continue

                # 检查API密钥
                if not provider.get('api_key'):
                    self.logger.warning(f"⚠️ 供应商 {provider.get('name', 'unknown')} 未配置API密钥，跳过")
                    continue

                try:
                    # 调用供应商API
                    result = self._call_provider_api(
                        provider,
                        prompt,
                        aspect_ratio,
                        image_size,
                        all_reference_images,
                        parts
                    )
                    response = result['response']
                    provider_name = result['provider_name']

                    # 检查响应状态
                    if response.status_code == 200:
                        self.logger.info(f"✅ 供应商 {provider_name} 请求成功")
                        break
                    else:
                        error_msg = f"供应商 {provider_name} 返回错误状态码: {response.status_code}"
                        self.logger.warning(f"⚠️ {error_msg}")
                        self.logger.debug(f"响应内容: {response.text[:500]}")
                        last_error = error_msg

                        # 如果是5xx错误或401认证错误，且还有其他供应商，尝试下一个
                        if (response.status_code >= 500 or response.status_code == 401) and attempt_idx < len(self.providers) - 1:
                            self.logger.info(f"🔄 状态码{response.status_code}，尝试切换到下一个供应商...")
                            continue
                        else:
                            # 没有更多供应商或不是可切换的错误，返回错误
                            break

                except requests.exceptions.Timeout as e:
                    error_msg = f"供应商 {provider.get('name', 'unknown')} 请求超时"
                    self.logger.warning(f"⏱️ {error_msg}: {e}")
                    last_error = error_msg
                    if attempt_idx < len(self.providers) - 1:
                        self.logger.info(f"🔄 尝试切换到下一个供应商...")
                        continue
                    else:
                        break

                except Exception as e:
                    error_msg = f"供应商 {provider.get('name', 'unknown')} 请求失败"
                    self.logger.error(f"❌ {error_msg}: {e}")
                    last_error = str(e)
                    if attempt_idx < len(self.providers) - 1:
                        self.logger.info(f"🔄 尝试切换到下一个供应商...")
                        continue
                    else:
                        break

            # 如果所有供应商都失败
            if not response or response.status_code != 200:
                error_msg = f"所有供应商都失败，最后错误: {last_error}"
                self.logger.error(f"❌ {error_msg}")
                return {
                    "success": False,
                    "error": error_msg,
                    "details": response.text if response else None
                }

            self.logger.info(f"📥 收到API响应:")
            self.logger.info(f"  - 状态码: {response.status_code}")
            self.logger.info(f"  - 响应大小: {len(response.content)} 字节")
            
            # 打印响应内容的预览（非base64部分）
            try:
                response_preview = response.text[:500] if response.text else "空响应"
                self.logger.info(f"  - 响应预览: {response_preview}...")
            except:
                pass

            # 解析响应
            try:
                response_data = response.json()
            except json.JSONDecodeError as e:
                self.logger.error(f"❌ JSON解析失败: {e}")
                self.logger.debug(f"响应内容前500字符: {response.text[:500]}")
                return {
                    "success": False,
                    "error": f"响应JSON解析失败: {str(e)}",
                    "response_text": response.text[:500]
                }
            
            self.logger.info(f"📋 解析响应数据...")
            self.logger.info(f"  - 响应顶层键: {list(response_data.keys())}")
            
            if 'candidates' in response_data:
                self.logger.info(f"  - 候选数量: {len(response_data['candidates'])}")
                if response_data['candidates']:
                    first_candidate = response_data['candidates'][0]
                    self.logger.info(f"  - 首个候选键: {list(first_candidate.keys())}")
            elif 'base64Image' in response_data:
                self.logger.info(f"  - 包含 base64Image 字段，数据长度: {len(response_data['base64Image'])} 字符")
            elif 'image' in response_data:
                self.logger.info(f"  - 包含 image 字段，数据长度: {len(response_data['image'])} 字符")
            elif 'data' in response_data:
                self.logger.info(f"  - 包含 data 字段，数据长度: {len(response_data['data'])} 字符")
            
            # 🔥 支持多种响应格式
            image_data = None
            text_response = None

            # 格式1: 标准 Gemini API 格式
            if 'candidates' in response_data and response_data['candidates']:
                candidate = response_data['candidates'][0]
                self.logger.debug(f"📋 候选响应结构")

                if 'content' in candidate and 'parts' in candidate['content']:
                    parts_count = len(candidate['content']['parts'])
                    self.logger.info(f"  - Parts数量: {parts_count}")

                    for idx, part in enumerate(candidate['content']['parts']):
                        part_keys = list(part.keys())
                        self.logger.info(f"  - Part {idx} 键: {part_keys}")

                        # 兼容 inlineData 和 inline_data 两种格式
                        if 'inlineData' in part:
                            image_data = part['inlineData'].get('data')
                            self.logger.info(f"✅ 从 inlineData 提取到图像数据 (长度: {len(image_data) if image_data else 0})")
                        elif 'inline_data' in part:
                            image_data = part['inline_data'].get('data')
                            self.logger.info(f"✅ 从 inline_data 提取到图像数据 (长度: {len(image_data) if image_data else 0})")
                        elif 'text' in part:
                            text_response = part['text']
                            self.logger.info(f"📝 提取到文本响应: {text_response[:100]}...")

            # 格式2: OpenAI 兼容格式 (AI-WX)
            elif 'data' in response_data and isinstance(response_data['data'], list):
                if response_data['data'] and 'b64_json' in response_data['data'][0]:
                    image_data = response_data['data'][0]['b64_json']
                    self.logger.info(f"✅ 从 OpenAI 格式提取到图像数据 (长度: {len(image_data) if image_data else 0})")
                elif response_data['data'] and 'url' in response_data['data'][0]:
                    # 如果返回的是URL，需要下载
                    image_url = response_data['data'][0]['url']
                    self.logger.info(f"📥 从URL下载图像: {image_url}")
                    try:
                        img_response = requests.get(image_url, timeout=30)
                        if img_response.status_code == 200:
                            image_data = base64.b64encode(img_response.content).decode('utf-8')
                            self.logger.info(f"✅ 成功下载并转换图像")
                    except Exception as e:
                        self.logger.error(f"❌ 下载图像失败: {e}")

            # 格式3: 直接包含 base64Image 字段
            elif 'base64Image' in response_data:
                image_data = response_data['base64Image']
                self.logger.debug(f"✅ 从 base64Image 字段提取到图像数据")

            # 格式4: 包含在 image 字段中
            elif 'image' in response_data:
                image_data = response_data['image']
                self.logger.debug(f"✅ 从 image 字段提取到图像数据")

            # 格式5: 包含在 data 字段中（字符串格式）
            elif 'data' in response_data and isinstance(response_data['data'], str):
                image_data = response_data['data']
                self.logger.debug(f"✅ 从 data 字段提取到图像数据")
            
            # 如果仍然没有找到图像数据，尝试从任何可能的字段中提取
            if not image_data:
                self.logger.debug(f"响应顶层键: {list(response_data.keys())}")
                
                # 递归搜索包含base64数据的字段
                def find_base64_in_dict(obj, depth=0):
                    if depth > 10:  # 防止无限递归
                        return None
                    
                    if isinstance(obj, dict):
                        for key, value in obj.items():
                            # 检查键名可能包含图像数据的字段
                            if any(keyword in key.lower() for keyword in ['image', 'photo', 'picture', 'base64', 'data', 'binary']):
                                if isinstance(value, str) and len(value) > 100:  # base64数据通常较长
                                    # 尝试解码验证是否为有效的base64
                                    try:
                                        base64.b64decode(value)
                                        self.logger.debug(f"✅ 从字段 '{key}' 找到可能的base64图像数据")
                                        return value
                                    except:
                                        pass
                            # 递归搜索
                            result = find_base64_in_dict(value, depth + 1)
                            if result:
                                return result
                    elif isinstance(obj, list):
                        for item in obj:
                            result = find_base64_in_dict(item, depth + 1)
                            if result:
                                return result
                    return None
                
                image_data = find_base64_in_dict(response_data)
            
            if not image_data:
                return {
                    "success": False,
                    "error": "未能从响应中提取图像数据",
                    "response_structure": list(response_data.keys()),
                    "text_response": text_response
                }
            
            # 解码base64图像数据
            try:
                image_bytes = base64.b64decode(image_data)
            except Exception as e:
                return {
                    "success": False,
                    "error": f"图像数据解码失败: {str(e)}"
                }
            
            # 生成保存路径
            if save_path is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                clean_name = "".join(x for x in prompt[:30] if x.isalnum() or x in (' ', '-', '_')).strip()
                clean_name = clean_name.replace(' ', '_')
                filename = f"nanobanana_{timestamp}_{clean_name}.png"
                save_path = str(self.output_dir / filename)
            
            # 保存图像
            with open(save_path, 'wb') as f:
                f.write(image_bytes)
            
            self.logger.info(f"✅ 图像生成成功!")
            self.logger.info(f"  - 保存路径: {save_path}")
            self.logger.info(f"  - 文件大小: {len(image_bytes)} 字节")
            if text_response:
                self.logger.info(f"  - 文本响应: {text_response[:100]}...")
            
            # 返回结果
            # 🔥 修复URL路径：如果save_path包含generated_images目录，则使用相对路径
            if 'generated_images' in save_path:
                # 提取从generated_images开始的相对路径
                rel_path = save_path.split('generated_images')[-1].replace('\\', '/')
                if rel_path.startswith('/'):
                    rel_path = rel_path[1:]
                # 🔥 对路径进行URL编码，支持中文字符
                encoded_path = quote(rel_path, safe='/')
                image_url = f"/generated_images/{encoded_path}"
            else:
                # 回退到只使用文件名
                filename = os.path.basename(save_path)
                encoded_filename = quote(filename, safe='')
                image_url = f"/generated_images/{encoded_filename}"

            return {
                "success": True,
                "local_path": save_path,
                "url": image_url,
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "image_size": image_size,
                "text_response": text_response,
                "file_size": len(image_bytes)
            }
            
        except requests.exceptions.Timeout:
            error_msg = f"请求超时 (超过{self.timeout}秒)"
            self.logger.error(error_msg)
            
            if retry_count < self.max_retries:
                self.logger.info(f"尝试重试 ({retry_count + 1}/{self.max_retries})...")
                return self.generate_image(prompt, aspect_ratio, image_size, save_path, retry_count + 1, reference_image, reference_images)
            
            return {
                "success": False,
                "error": error_msg
            }
            
        except Exception as e:
            error_msg = f"生成图像时发生错误: {str(e)}"
            self.logger.error(error_msg)
            import traceback
            self.logger.error(traceback.format_exc())
            
            return {
                "success": False,
                "error": error_msg
            }
    
    def batch_generate(
        self,
        prompts: List[str],
        aspect_ratio: str = "16:9",
        image_size: str = "4K",
        delay: float = 1.0
    ) -> List[Dict[str, Any]]:
        """
        批量生成图像
        
        Args:
            prompts: 提示词列表
            aspect_ratio: 图片比例
            image_size: 图片尺寸
            delay: 请求间隔(秒)
            
        Returns:
            list: 生成结果列表
        """
        results = []
        
        for i, prompt in enumerate(prompts):
            self.logger.info(f"正在生成第 {i+1}/{len(prompts)} 张图像...")
            
            try:
                result = self.generate_image(
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    image_size=image_size
                )
                result['index'] = i + 1
                result['prompt'] = prompt
                results.append(result)
                
                # 避免频繁调用，添加延迟
                if delay > 0 and i < len(prompts) - 1:
                    import time
                    time.sleep(delay)
                    
            except Exception as e:
                self.logger.error(f"生成第 {i+1} 张图像时出错: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "index": i + 1,
                    "prompt": prompt
                })
        
        success_count = len([r for r in results if r.get('success')])
        self.logger.info(f"🎉 批量生成完成: {success_count}/{len(prompts)} 成功")
        
        return results
    
    def is_available(self) -> bool:
        """
        检查服务是否可用
        
        Returns:
            bool: 服务是否可用
        """
        return self.enabled and bool(self.api_key)
    
    def add_text_watermark(
        self,
        image_path: str,
        text: str,
        position: str = 'bottom_right',
        font_size: int = 24,
        text_color: tuple = (255, 255, 255),
        bg_color: tuple = (0, 0, 0, 180),
        padding: int = 10
    ) -> str:
        """
        给图片添加文字水印
        
        Args:
            image_path: 图片路径
            text: 要添加的文字
            position: 位置 ('bottom_right', 'bottom_left', 'top_right', 'top_left', 'center')
            font_size: 字体大小
            text_color: 文字颜色 (R, G, B)
            bg_color: 背景颜色 (R, G, B, A)
            padding: 内边距
            
        Returns:
            str: 处理后图片的路径
        """
        if not PIL_AVAILABLE:
            self.logger.warning("⚠️ PIL未安装，无法添加文字水印")
            return image_path
        
        try:
            # 打开图片
            img = Image.open(image_path)
            
            # 转换为RGBA模式（支持透明）
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # 创建绘图对象
            draw = ImageDraw.Draw(img)
            
            # 尝试使用系统字体，如果不存在则使用默认字体
            try:
                # 尝试使用常见的系统字体
                font_paths = [
                    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',  # Linux
                    '/System/Library/Fonts/Helvetica.ttc',  # macOS
                    'C:/Windows/Fonts/arial.ttf',  # Windows
                    'C:/Windows/Fonts/simhei.ttf',  # Windows 黑体（支持中文）
                    'C:/Windows/Fonts/simsun.ttc',  # Windows 宋体
                ]
                font = None
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        font = ImageFont.truetype(font_path, font_size)
                        break
                
                if font is None:
                    font = ImageFont.load_default()
            except Exception:
                font = ImageFont.load_default()
            
            # 计算文字尺寸
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            
            # 计算位置
            img_width, img_height = img.size
            
            if position == 'bottom_right':
                x = img_width - text_width - padding * 2
                y = img_height - text_height - padding * 2
            elif position == 'bottom_left':
                x = padding
                y = img_height - text_height - padding * 2
            elif position == 'top_right':
                x = img_width - text_width - padding * 2
                y = padding
            elif position == 'top_left':
                x = padding
                y = padding
            elif position == 'center':
                x = (img_width - text_width) // 2
                y = (img_height - text_height) // 2
            else:
                x = img_width - text_width - padding * 2
                y = img_height - text_height - padding * 2
            
            # 绘制半透明背景
            overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle(
                [x - padding, y - padding, x + text_width + padding, y + text_height + padding],
                fill=bg_color
            )
            
            # 合并图层
            img = Image.alpha_composite(img, overlay)
            
            # 重新创建绘图对象
            draw = ImageDraw.Draw(img)
            
            # 绘制文字
            draw.text((x, y), text, font=font, fill=text_color)
            
            # 转换回RGB（去除透明通道）
            img = img.convert('RGB')
            
            # 保存图片
            img.save(image_path, 'PNG')
            
            self.logger.info(f"✅ 已添加文字水印: {text}")
            return image_path
            
        except Exception as e:
            self.logger.error(f"❌ 添加文字水印失败: {e}")
            import traceback
            self.logger.error(traceback.format_exc())
            return image_path
    
    def generate_character_model_sheet(
        self,
        name: str,
        character_id: str = '',
        bilingual_desc: dict = None,
        save_path: Optional[str] = None,
        image_size: str = '4K'
    ) -> Dict[str, Any]:
        """
        生成角色设计表 (Character Design Sheet) - 使用中英双语描述和角色ID
        
        Args:
            name: 角色名称
            character_id: 角色唯一ID（用于AI识别匹配）
            bilingual_desc: 中英双语描述字典 {chinese, english, tags}
            save_path: 保存路径
            image_size: 图片尺寸 (1K/2K/4K)
            
        Returns:
            dict: 包含生成结果的字典
        """
        if not self.is_available():
            return {"success": False, "error": "服务不可用"}
        
        if not bilingual_desc:
            return {"success": False, "error": "缺少双语描述"}
        
        self.logger.info(f"🎨 开始生成角色设计表: {name} (ID: {character_id})")
        
        # 提取双语描述
        chinese_desc = bilingual_desc.get('chinese', name)
        english_desc = bilingual_desc.get('english', name)
        tags = bilingual_desc.get('tags', [name])
        
        # 构建角色ID标签（用于AI识别匹配）
        char_tag = f"CHARACTER_ID_{character_id.upper().replace(' ', '_')}"
        
        # ============================================
        # 构建3D角色模型表格提示词（单张图四视图）
        # ============================================
        final_prompt = f"""[3D CHARACTER MODEL SHEET] [ID: {char_tag}]

Character: {name} - {english_desc}
Ethnicity: East Asian, Chinese facial features
Style: 3D stylized render, Unreal Engine 5 quality, PBR materials

SINGLE IMAGE containing four views of the same character arranged in a grid:
- Top-left: Front headshot close-up, neutral expression
- Top-right: Front full body in T-pose (0° angle)
- Bottom-left: Side full body in T-pose (90° side profile)
- Bottom-right: Back full body in T-pose (180° back view)

All four views in ONE image, same character, same outfit, same hairstyle. Character turnaround reference sheet format.

TECHNICAL: 3D render, Octane quality, ray tracing, PBR textures, orthographic views, white background, 8k, professional model sheet, {', '.join(tags[:3])}

NEGATIVE: 2D illustration, sketch, anime drawing, flat color, manga, painting, watercolor, cel-shaded, chibi, hand-drawn, Western face, separate images, multiple images, low quality"""

        self.logger.info(f"📝 四视图提示词长度: {len(final_prompt)} chars")
        self.logger.info(f"📝 提示词预览: {final_prompt[:300]}...")
        
        # 使用16:9比例生成单张四视图
        result = self.generate_image(
            prompt=final_prompt,
            aspect_ratio='16:9',
            image_size=image_size,
            save_path=save_path
        )
        
        if result.get('success'):
            self.logger.info(f"✅ 角色设计表生成成功: {result.get('local_path')}")
        else:
            self.logger.error(f"❌ 角色设计表生成失败: {result.get('error')}")
        
        return result



def main():
    """测试函数"""
    try:
        # 初始化生成器
        generator = NanoBananaImageGenerator()
        
        if not generator.is_available():
            print("❌ Nano Banana服务不可用，请检查配置")
            return
        
        # 测试提示词
        test_prompt = "a cute cat sitting on a red cushion, cartoon style, vibrant colors"
        
        print("🎨 开始测试生成图像...")
        result = generator.generate_image(
            prompt=test_prompt,
            aspect_ratio="16:9",
            image_size="2K"
        )
        
        if result["success"]:
            print(f"✅ 测试成功!")
            print(f"   图像路径: {result['local_path']}")
            print(f"   访问URL: {result['url']}")
            if result.get('text_response'):
                print(f"   文本响应: {result['text_response']}")
        else:
            print(f"❌ 测试失败: {result['error']}")
            
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()