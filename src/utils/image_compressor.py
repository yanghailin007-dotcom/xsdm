"""
图片压缩工具
用于压缩上传到 VeO API 的图片，避免 "message too large" 错误
"""
import base64
import io
from typing import Optional, Tuple
from PIL import Image
from src.utils.logger import get_logger

logger = get_logger(__name__)

# VeO API 最大请求体大小限制（保守估计）
MAX_IMAGE_SIZE_MB = 2
MAX_IMAGE_SIZE_BYTES = MAX_IMAGE_SIZE_MB * 1024 * 1024

# 推荐的压缩质量
DEFAULT_QUALITY = 85
MIN_QUALITY = 60

# 推荐的最大尺寸
MAX_DIMENSION = 1920  # 1920x1920


def compress_image(
    image_data: str,
    max_size_mb: float = MAX_IMAGE_SIZE_MB,
    quality: int = DEFAULT_QUALITY,
    max_dimension: int = MAX_DIMENSION
) -> str:
    """
    压缩 base64 编码的图片
    
    Args:
        image_data: base64 编码的图片数据
        max_size_mb: 最大允许大小（MB）
        quality: JPEG 压缩质量 (1-100)
        max_dimension: 最大边长（像素）
    
    Returns:
        压缩后的 base64 编码图片数据
    """
    try:
        # 解码 base64
        if ',' in image_data:
            # 移除 data URL 前缀（如果有）
            image_data = image_data.split(',', 1)[1]
        
        image_bytes = base64.b64decode(image_data)
        
        # 检查原始大小
        original_size = len(image_bytes)
        original_size_mb = original_size / (1024 * 1024)
        
        logger.info(f"📸 原始图片大小: {original_size_mb:.2f} MB")
        
        # 如果已经足够小，直接返回
        if original_size <= max_size_mb * 1024 * 1024:
            logger.info(f"✅ 图片大小符合要求，无需压缩")
            return image_data
        
        # 打开图片
        img = Image.open(io.BytesIO(image_bytes))
        
        # 转换为 RGB（如果是 RGBA）
        if img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
            img = background
        elif img.mode != 'RGB':
            img = img.convert('RGB')
        
        # 调整尺寸（如果需要）
        width, height = img.size
        if max(width, height) > max_dimension:
            logger.info(f"🔄 调整图片尺寸: {width}x{height} -> ")
            if width > height:
                new_width = max_dimension
                new_height = int(height * (max_dimension / width))
            else:
                new_height = max_dimension
                new_width = int(width * (max_dimension / height))
            
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            logger.info(f"{new_width}x{new_height}")
        
        # 逐步压缩直到满足大小要求
        current_quality = quality
        output_buffer = io.BytesIO()
        
        while current_quality >= MIN_QUALITY:
            output_buffer.seek(0)
            output_buffer.truncate()
            
            # 保存为 JPEG
            img.save(output_buffer, format='JPEG', quality=current_quality, optimize=True)
            
            compressed_size = output_buffer.tell()
            compressed_size_mb = compressed_size / (1024 * 1024)
            
            logger.info(f"🔄 质量 {current_quality}: {compressed_size_mb:.2f} MB")
            
            if compressed_size <= max_size_mb * 1024 * 1024:
                # 压缩成功
                compressed_data = output_buffer.getvalue()
                base64_data = base64.b64encode(compressed_data).decode('utf-8')
                
                compression_ratio = (1 - compressed_size / original_size) * 100
                logger.info(f"✅ 压缩成功: {original_size_mb:.2f} MB -> {compressed_size_mb:.2f} MB "
                          f"({compression_ratio:.1f}% 减少)")
                
                return base64_data
            
            # 降低质量重试
            current_quality -= 5
        
        # 如果仍然太大，使用最小质量
        logger.warn(f"⚠️  使用最低质量 {MIN_QUALITY} 仍然超过大小限制")
        compressed_data = output_buffer.getvalue()
        base64_data = base64.b64encode(compressed_data).decode('utf-8')
        
        return base64_data
    
    except Exception as e:
        logger.error(f"❌ 图片压缩失败: {e}")
        # 返回原始数据
        return image_data


def validate_and_compress_images(
    images: list,
    max_size_mb: float = MAX_IMAGE_SIZE_MB,
    quality: int = DEFAULT_QUALITY
) -> Tuple[list, dict]:
    """
    验证并压缩图片列表
    
    Args:
        images: base64 图片列表
        max_size_mb: 最大允许大小（MB）
        quality: JPEG 压缩质量
    
    Returns:
        (压缩后的图片列表, 压缩统计信息)
    """
    compressed_images = []
    stats = {
        'total': len(images),
        'compressed': 0,
        'skipped': 0,
        'failed': 0,
        'total_original_size_mb': 0,
        'total_compressed_size_mb': 0
    }
    
    for i, img in enumerate(images):
        try:
            if not img or not isinstance(img, str):
                logger.warn(f"⚠️  图片 {i} 数据无效，跳过")
                stats['failed'] += 1
                continue
            
            # 计算原始大小
            if ',' in img:
                img_data = img.split(',', 1)[1]
            else:
                img_data = img
            
            original_bytes = len(base64.b64decode(img_data))
            stats['total_original_size_mb'] = stats.get('total_original_size_mb', 0.0) + original_bytes / (1024 * 1024)
            
            # 压缩图片
            compressed = compress_image(img, max_size_mb, quality)
            compressed_images.append(compressed)
            
            # 计算压缩后大小
            compressed_bytes = len(base64.b64decode(compressed))
            stats['total_compressed_size_mb'] = stats.get('total_compressed_size_mb', 0.0) + compressed_bytes / (1024 * 1024)
            
            if compressed_bytes < original_bytes:
                stats['compressed'] += 1
            else:
                stats['skipped'] += 1
        
        except Exception as e:
            logger.error(f"❌ 处理图片 {i} 失败: {e}")
            stats['failed'] += 1
    
    # 计算总体压缩率
    if stats['total_original_size_mb'] > 0:
        stats['compression_ratio'] = (
            1 - stats['total_compressed_size_mb'] / stats['total_original_size_mb']
        ) * 100
    else:
        stats['compression_ratio'] = 0
    
    logger.info(f"📊 压缩统计:")
    logger.info(f"  总数: {stats['total']}")
    logger.info(f"  压缩: {stats['compressed']}")
    logger.info(f"  跳过: {stats['skipped']}")
    logger.info(f"  失败: {stats['failed']}")
    logger.info(f"  总大小: {stats['total_original_size_mb']:.2f} MB -> "
               f"{stats['total_compressed_size_mb']:.2f} MB")
    logger.info(f"  压缩率: {stats['compression_ratio']:.1f}%")
    
    return compressed_images, stats


if __name__ == "__main__":
    # 测试
    print("图片压缩工具测试")
    print(f"最大图片大小: {MAX_IMAGE_SIZE_MB} MB")
    print(f"默认质量: {DEFAULT_QUALITY}")
    print(f"最小质量: {MIN_QUALITY}")
    print(f"最大尺寸: {MAX_DIMENSION}x{MAX_DIMENSION}")