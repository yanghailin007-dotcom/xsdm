"""
导出功能 API
处理视频、音频、字幕、小说项目等文件的打包导出
"""
import os
import json
import zipfile
import tempfile
import requests
from io import BytesIO
from pathlib import Path
from flask import Blueprint, request, jsonify, send_file
from datetime import datetime

export_api = Blueprint('export_api', __name__, url_prefix='/api/export')

# 视频项目目录
VIDEO_PROJECTS_DIR = Path(__file__).parent.parent.parent / '视频项目'

# 小说项目目录
NOVEL_PROJECTS_DIR = Path(__file__).parent.parent.parent / '小说项目'


@export_api.route('/videos-zip', methods=['POST'])
def export_videos_zip():
    """
    批量导出视频为 ZIP 文件
    """
    try:
        data = request.get_json()
        novel_title = data.get('novel_title')
        episode_title = data.get('episode_title')
        shots = data.get('shots', [])
        
        if not novel_title or not episode_title:
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400
        
        if not shots:
            return jsonify({'success': False, 'error': '没有可导出的视频'}), 400
        
        # 创建临时 ZIP 文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        temp_file.close()
        
        with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zf:
            for shot in shots:
                video_url = shot.get('video_url')
                if not video_url:
                    continue
                
                try:
                    # 下载视频文件
                    response = requests.get(video_url, timeout=60, stream=True)
                    if response.status_code == 200:
                        # 构建文件名
                        scene_num = shot.get('scene_number', 1)
                        shot_num = shot.get('shot_number', 1)
                        shot_type = shot.get('shot_type', '镜头')
                        
                        # 清理文件名中的非法字符
                        safe_type = ''.join(c for c in shot_type if c.isalnum() or c in ' _-')
                        filename = f"S{scene_num:02d}_#{shot_num:02d}_{safe_type}.mp4"
                        
                        # 添加到 ZIP
                        zf.writestr(filename, response.content)
                except Exception as e:
                    print(f"下载视频失败 {video_url}: {e}")
                    continue
        
        return send_file(
            temp_file.name,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{episode_title}_视频合集_{len(shots)}个.zip"
        )
        
    except Exception as e:
        print(f"导出视频 ZIP 失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@export_api.route('/complete-package', methods=['POST'])
def export_complete_package():
    """
    一键打包全部内容（视频+音频+字幕+配置）
    """
    try:
        data = request.get_json()
        novel_title = data.get('novel_title')
        episode_title = data.get('episode_title')
        
        if not novel_title or not episode_title:
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400
        
        # 构建项目路径
        project_dir = VIDEO_PROJECTS_DIR / novel_title / episode_title
        if not project_dir.exists():
            return jsonify({'success': False, 'error': '项目目录不存在'}), 404
        
        # 创建临时 ZIP 文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        temp_file.close()
        
        with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1. 添加视频文件
            video_dir = project_dir / 'videos'
            if video_dir.exists():
                for video_file in video_dir.glob('*.mp4'):
                    zf.write(video_file, f"01_视频/{video_file.name}")
            
            # 2. 添加音频文件
            audio_dir = project_dir / 'audio'
            if audio_dir.exists():
                for audio_file in audio_dir.glob('*.mp3'):
                    zf.write(audio_file, f"02_音频/{audio_file.name}")
            
            # 3. 添加字幕文件
            subtitle_file = project_dir / 'subtitle.srt'
            if subtitle_file.exists():
                zf.write(subtitle_file, f"03_字幕/{subtitle_file.name}")
            
            # 4. 添加配置文件
            shots_file = project_dir / 'shots_v2.json'
            if shots_file.exists():
                zf.write(shots_file, f"04_配置/shots_v2.json")
            
            # 5. 添加项目信息
            project_info_file = project_dir / '项目信息.json'
            if project_info_file.exists():
                zf.write(project_info_file, f"04_配置/项目信息.json")
            
            # 6. 添加 README 说明文件
            readme_content = f"""# {episode_title} - 成片导出包

导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 目录结构

- 01_视频/ - 所有生成的视频文件
- 02_音频/ - 配音音频文件
- 03_字幕/ - SRT 格式字幕文件
- 04_配置/ - 项目配置文件和分镜数据

## 使用说明

1. 视频文件按场景和镜头编号命名
2. 音频文件可与视频合并使用
3. 字幕文件支持导入剪映、Premiere 等软件
4. 配置文件包含完整的分镜和提示词信息

## 项目信息

- 小说: {novel_title}
- 集数: {episode_title}
- 生成平台: 短剧工作台
"""
            zf.writestr("README.md", readme_content)
        
        return send_file(
            temp_file.name,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{episode_title}_完整成片包.zip"
        )
        
    except Exception as e:
        print(f"导出完整包失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@export_api.route('/novel-zip/<title>', methods=['GET'])
def export_novel_zip(title):
    """
    打包导出小说项目所有文件为 ZIP
    
    包含：
    - 章节内容 (txt)
    - 项目配置 (json)
    - 世界观设定
    - 角色设计
    - 写作计划
    """
    try:
        # 使用 NovelGenerationManager 查找项目路径
        from web.managers.novel_manager import NovelGenerationManager
        manager = NovelGenerationManager()
        
        # 获取项目详细信息以确定正确路径
        novel_detail = manager.get_novel_detail(title)
        if not novel_detail:
            return jsonify({'success': False, 'error': '小说项目不存在'}), 404
        
        # 构建小说项目完整路径 (owner/title 结构)
        owner = novel_detail.get('owner', 'anonymous')
        project_dir = NOVEL_PROJECTS_DIR / owner / title
        if not project_dir.exists():
            # 尝试直接查找（兼容旧结构）
            project_dir = NOVEL_PROJECTS_DIR / title
            if not project_dir.exists():
                return jsonify({'success': False, 'error': '小说项目路径不存在'}), 404
        
        # 创建临时 ZIP 文件
        temp_file = tempfile.NamedTemporaryFile(suffix='.zip', delete=False)
        temp_file.close()
        
        with zipfile.ZipFile(temp_file.name, 'w', zipfile.ZIP_DEFLATED) as zf:
            # 1. 添加章节内容
            chapters_dir = project_dir / 'chapters'
            if chapters_dir.exists():
                for chapter_file in chapters_dir.glob('*.txt'):
                    zf.write(chapter_file, f"01_章节内容/{chapter_file.name}")
            
            # 2. 添加项目配置
            config_file = project_dir / 'novel_data.json'
            if config_file.exists():
                zf.write(config_file, f"02_项目配置/novel_data.json")
            
            # 3. 添加核心设定文件
            core_files = [
                ('creative_seed.json', '创意种子'),
                ('selected_plan.json', '选定方案'),
                ('core_worldview.json', '核心世界观'),
                ('character_design.json', '角色设计'),
                ('overall_stage_plans.json', '阶段大纲'),
            ]
            for filename, desc in core_files:
                file_path = project_dir / filename
                if file_path.exists():
                    zf.write(file_path, f"03_核心设定/{filename}")
            
            # 4. 添加阶段写作计划
            stage_plans_dir = project_dir / 'stage_plans'
            if stage_plans_dir.exists():
                for stage_file in stage_plans_dir.glob('*_writing_plan.json'):
                    zf.write(stage_file, f"04_写作计划/{stage_file.name}")
            
            # 5. 添加势力系统
            factions_file = project_dir / 'factions' / 'factions.json'
            if factions_file.exists():
                zf.write(factions_file, f"05_势力系统/factions.json")
            
            # 6. 添加情感蓝图
            emotional_file = project_dir / 'emotional_blueprint.json'
            if emotional_file.exists():
                zf.write(emotional_file, f"06_情感蓝图/emotional_blueprint.json")
            
            # 7. 添加成长规划
            growth_file = project_dir / 'growth_plan.json'
            if growth_file.exists():
                zf.write(growth_file, f"07_成长规划/growth_plan.json")
            
            # 8. 添加完整小说文本（合并所有章节）
            full_text = []
            full_text.append(f"# {title}")
            full_text.append(f"导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            full_text.append("=" * 50)
            full_text.append("")
            
            # 尝试读取章节内容
            if chapters_dir.exists():
                chapter_files = sorted(chapters_dir.glob('*.txt'))
                for chapter_file in chapter_files:
                    try:
                        with open(chapter_file, 'r', encoding='utf-8') as f:
                            full_text.append(f.read())
                            full_text.append("\n\n")
                    except Exception as e:
                        print(f"读取章节失败 {chapter_file}: {e}")
            
            if len(full_text) > 4:  # 如果有内容
                zf.writestr(f"00_完整小说.txt", "\n".join(full_text))
            
            # 9. 添加 README 说明文件
            readme_content = f"""# {title} - 小说项目导出包

导出时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 目录结构

- 00_完整小说.txt - 合并所有章节的完整小说文本
- 01_章节内容/ - 各章节独立文本文件
- 02_项目配置/ - 项目基础配置 (novel_data.json)
- 03_核心设定/ - 创意种子、世界观、角色设计等
- 04_写作计划/ - 各阶段详细写作计划
- 05_势力系统/ - 势力关系配置
- 06_情感蓝图/ - 情感线规划
- 07_成长规划/ - 角色成长规划

## 使用说明

1. **完整小说.txt**: 直接阅读或导入到 Word 等软件
2. **章节内容/**: 单独查看或编辑各章节
3. **项目配置/**: 包含项目的完整数据，可用于恢复项目
4. **核心设定/**: 查看 AI 生成的世界观和角色设定

## 注意事项

- 此导出包包含项目的所有数据，请妥善保管
- 如需恢复项目，将文件解压后放回原项目目录即可
- 建议定期导出备份重要项目
"""
            zf.writestr("README.md", readme_content)
        
        return send_file(
            temp_file.name,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{title}_小说项目导出.zip"
        )
        
    except Exception as e:
        print(f"导出小说 ZIP 失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
