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
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            readme_content = f"""# {episode_title} - 成片导出包

导出时间: {now_str}

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
    打包导出小说/短篇项目所有文件为 ZIP
    
    包含：
    - 章节内容 (txt)
    - 项目配置 (json)
    - 世界观设定（长篇）
    - 角色设计（长篇）
    - 写作计划（长篇）
    """
    try:
        from urllib.parse import unquote
        from pathlib import Path
        title = unquote(title)
        
        # 使用 path_utils 动态查找用户项目（支持 owner/title 结构）
        from web.utils.path_utils import list_user_projects, list_user_short_stories, is_admin, get_short_stories_root
        
        # 获取当前用户（从 session 或请求上下文）
        from flask import session
        try:
            username = session.get('username')
        except RuntimeError:
            username = None
        
        # 检查用户是否登录
        if not username:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        
        # 检查是否为短篇
        short_stories = list_user_short_stories(username)
        is_short_story = any(s['title'] == title for s in short_stories)
        
        if is_short_story:
            # 🔥 短篇作品导出
            story = next(s for s in short_stories if s['title'] == title)
            project_dir = Path(story['path'])
            if not project_dir.exists():
                return jsonify({'success': False, 'error': '短篇作品路径不存在'}), 404
        else:
            # 🔥 长篇作品导出
            user_projects = list_user_projects(username, include_public=True)
            target_project = None
            for project in user_projects:
                if project['title'] == title:
                    target_project = project
                    break
            
            if not target_project:
                return jsonify({'success': False, 'error': '小说项目不存在或无权访问'}), 404
            
            # 构建小说项目完整路径 (owner/title 结构)
            owner = target_project.get('owner', username)
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
            # 递归导出项目目录中的所有文件
            file_count = 0
            for item in project_dir.rglob('*'):
                if item.is_file():
                    # 计算相对路径
                    arcname = item.relative_to(project_dir)
                    try:
                        zf.write(item, arcname)
                        file_count += 1
                    except Exception as e:
                        print(f"添加文件失败 {item}: {e}")
            
            # 尝试合并章节内容（如果存在chapters目录）
            chapters_dir = project_dir / 'chapters'
            if chapters_dir.exists():
                full_text = []
                full_text.append(f"# {title}")
                now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                full_text.append(f"导出时间: {now_str}")
                full_text.append("=" * 50)
                full_text.append("")
                
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
                    file_count += 1
            
            # 9. 添加 README 说明文件
            now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            if is_short_story:
                readme_content = f"""# {title} - 短篇作品导出包

导出时间: {now_str}
共导出 {file_count} 个文件
作品类型: 短篇

## 目录结构

本导出包包含短篇作品的完整文件结构：

- outline.json - 大纲和简介
- chapters/ - 章节内容
- 00_完整小说.txt (如存在章节) - 合并所有章节的完整小说文本

## 使用说明

1. 解压后可直接阅读 00_完整小说.txt 查看完整内容
2. chapters/ 目录包含各章节的独立文件
3. outline.json 包含作品的大纲信息

## 注意事项

- 此导出包包含作品的完整数据，请妥善保管
- 短篇作品可直接用于投稿、发布到知乎/公众号等平台
"""
            else:
                readme_content = f"""# {title} - 小说项目导出包

导出时间: {now_str}
共导出 {file_count} 个文件
作品类型: 长篇

## 目录结构

本导出包包含项目的完整文件结构：

- project_info/ - 项目信息配置
- 写作计划/ - 各阶段写作计划
- 生成材料/ - AI生成的设定材料
- 数据文件/ - 项目数据文件
- *_项目信息.json - 项目元数据
- *_writing_style_guide.json - 写作风格指南
- 00_完整小说.txt (如存在章节) - 合并所有章节的完整小说文本

## 使用说明

1. 解压后将文件夹放回原项目目录即可恢复项目
2. 包含所有AI生成的设定、大纲、写作计划
3. 如有章节内容，可在 00_完整小说.txt 中查看

## 注意事项

- 此导出包包含项目的所有数据，请妥善保管
- 建议定期导出备份重要项目
"""
            zf.writestr("README.md", readme_content)
        
        return send_file(
            temp_file.name,
            mimetype='application/zip',
            as_attachment=True,
            download_name=f"{title}_{'短篇' if is_short_story else '小说项目'}导出.zip"
        )
        
    except Exception as e:
        print(f"导出小说 ZIP 失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@export_api.route('/novel-preview', methods=['GET'])
def export_novel_preview():
    """
    获取小说/短篇预览数据（用于导出页面预览）
    """
    try:
        from urllib.parse import unquote
        from web.utils.path_utils import list_user_projects, list_user_short_stories, get_current_username
        from flask import session
        from pathlib import Path
        import json
        
        title = request.args.get('title', '')
        title = unquote(title)
        
        if not title:
            return jsonify({'success': False, 'error': '缺少小说标题'}), 400
        
        # 获取当前用户
        try:
            username = session.get('username')
        except RuntimeError:
            username = None
        
        if not username:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        
        # 检查是否为短篇
        short_stories = list_user_short_stories(username)
        is_short_story = any(s['title'] == title for s in short_stories)
        
        chapter_list = []
        synopsis = ''
        
        if is_short_story:
            # 🔥 短篇作品处理
            story = next(s for s in short_stories if s['title'] == title)
            story_path = Path(story['path'])
            
            # 读取 outline.json 获取简介
            outline_path = story_path / 'outline.json'
            if outline_path.exists():
                try:
                    with open(outline_path, 'r', encoding='utf-8') as f:
                        outline = json.load(f)
                        synopsis = outline.get('synopsis', '')
                except Exception:
                    pass
            
            # 读取章节
            chapters_dir = story_path / 'chapters'
            if chapters_dir.exists():
                chapter_files = sorted(chapters_dir.glob('chapter_*.json'))
                for i, ch_file in enumerate(chapter_files, 1):
                    try:
                        with open(ch_file, 'r', encoding='utf-8') as f:
                            ch_data = json.load(f)
                        chapter_list.append({
                            'number': ch_data.get('chapter_number', i),
                            'title': ch_data.get('title', f'第{i}章'),
                            'content': ch_data.get('content', '')[:1000]
                        })
                    except Exception:
                        pass
        else:
            # 🔥 长篇作品处理
            user_projects = list_user_projects(username, include_public=True)
            target_project = None
            for project in user_projects:
                if project['title'] == title:
                    target_project = project
                    break
            
            if not target_project:
                return jsonify({'success': False, 'error': '小说项目不存在或无权访问'}), 404
            
            # 获取章节数据
            from src.utils.path_manager import path_manager
            owner = target_project.get('owner', username)
            chapters = path_manager.get_all_chapters(title, username=owner)
            
            # 格式化章节数据
            for num in sorted(chapters.keys()):
                chapter = chapters[num]
                chapter_list.append({
                    'number': num,
                    'title': chapter.get('chapter_title', f'第{num}章'),
                    'content': chapter.get('content', '')[:1000]
                })
            
            # 获取简介
            try:
                project_info_path = Path('小说项目') / owner / title / 'project_info.json'
                if not project_info_path.exists():
                    project_info_path = Path('小说项目') / f"{title}_项目信息.json"
                if project_info_path.exists():
                    with open(project_info_path, 'r', encoding='utf-8') as f:
                        project_info = json.load(f)
                        synopsis = project_info.get('synopsis', '') or project_info.get('story_synopsis', '')
            except Exception:
                pass
        
        return jsonify({
            'success': True,
            'title': title,
            'synopsis': synopsis,
            'chapters': chapter_list,
            'total_chapters': len(chapter_list),
            'is_short_story': is_short_story
        })
        
    except Exception as e:
        print(f"获取预览数据失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@export_api.route('/novel-content', methods=['GET'])
def export_novel_content():
    """
    导出小说/短篇正文内容为 TXT 或 Markdown
    
    参数:
        - title: 小说标题
        - format: 格式 (txt|md)
        - include_title: 是否包含章节标题
        - include_synopsis: 是否包含简介
        - add_separator: 是否添加分隔线
        - start_chapter: 起始章节
        - end_chapter: 结束章节
    """
    try:
        from urllib.parse import unquote
        from web.utils.path_utils import list_user_projects, list_user_short_stories
        from flask import session, make_response
        from pathlib import Path
        
        title = request.args.get('title', '')
        title = unquote(title)
        format_type = request.args.get('format', 'txt')
        include_title = request.args.get('include_title', 'true').lower() == 'true'
        include_synopsis = request.args.get('include_synopsis', 'true').lower() == 'true'
        add_separator = request.args.get('add_separator', 'true').lower() == 'true'
        start_chapter = int(request.args.get('start_chapter', 1))
        end_chapter = int(request.args.get('end_chapter', 9999))
        
        if not title:
            return jsonify({'success': False, 'error': '缺少小说标题'}), 400
        
        # 获取当前用户
        try:
            username = session.get('username')
        except RuntimeError:
            username = None
        
        if not username:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        
        # 检查是否为短篇
        short_stories = list_user_short_stories(username)
        is_short_story = any(s['title'] == title for s in short_stories)
        
        chapters = {}
        synopsis = ''
        
        if is_short_story:
            # 🔥 短篇作品处理
            story = next(s for s in short_stories if s['title'] == title)
            story_path = Path(story['path'])
            
            # 读取 outline.json 获取简介
            outline_path = story_path / 'outline.json'
            if outline_path.exists():
                try:
                    with open(outline_path, 'r', encoding='utf-8') as f:
                        outline = json.load(f)
                        synopsis = outline.get('synopsis', '')
                except Exception:
                    pass
            
            # 读取章节
            chapters_dir = story_path / 'chapters'
            if chapters_dir.exists():
                chapter_files = sorted(chapters_dir.glob('chapter_*.json'))
                for ch_file in chapter_files:
                    try:
                        with open(ch_file, 'r', encoding='utf-8') as f:
                            ch_data = json.load(f)
                        ch_num = ch_data.get('chapter_number', 0)
                        chapters[ch_num] = {
                            'chapter_title': ch_data.get('title', f'第{ch_num}章'),
                            'content': ch_data.get('content', '')
                        }
                    except Exception:
                        pass
        else:
            # 🔥 长篇作品处理
            user_projects = list_user_projects(username, include_public=True)
            target_project = None
            for project in user_projects:
                if project['title'] == title:
                    target_project = project
                    break
            
            if not target_project:
                return jsonify({'success': False, 'error': '小说项目不存在或无权访问'}), 404
            
            # 获取章节数据
            from src.utils.path_manager import path_manager
            owner = target_project.get('owner', username)
            chapters = path_manager.get_all_chapters(title, username=owner)
            
            # 获取简介
            if include_synopsis:
                try:
                    project_info_path = Path('小说项目') / owner / title / 'project_info.json'
                    if not project_info_path.exists():
                        project_info_path = Path('小说项目') / f"{title}_项目信息.json"
                    if project_info_path.exists():
                        with open(project_info_path, 'r', encoding='utf-8') as f:
                            project_info = json.load(f)
                            synopsis = project_info.get('synopsis', '') or project_info.get('story_synopsis', '')
                except Exception:
                    pass
        
        # 获取简介（从项目信息文件）
        synopsis = ''
        if include_synopsis:
            try:
                import json
                from pathlib import Path
                project_info_path = Path('小说项目') / owner / title / 'project_info.json'
                if not project_info_path.exists():
                    project_info_path = Path('小说项目') / f"{title}_项目信息.json"
                if project_info_path.exists():
                    with open(project_info_path, 'r', encoding='utf-8') as f:
                        project_info = json.load(f)
                        synopsis = project_info.get('synopsis', '') or project_info.get('story_synopsis', '')
            except Exception:
                pass
        
        # 生成内容
        content_lines = []
        
        # 标题
        if format_type == 'md':
            content_lines.append(f"# {title}")
            content_lines.append("")
        else:
            content_lines.append(title)
            content_lines.append("=" * len(title))
            content_lines.append("")
        
        # 简介
        if synopsis:
            if format_type == 'md':
                content_lines.append("## 简介")
                content_lines.append("")
                content_lines.append(synopsis)
                content_lines.append("")
                content_lines.append("---")
                content_lines.append("")
            else:
                content_lines.append("【简介】")
                content_lines.append(synopsis)
                content_lines.append("")
                content_lines.append("=" * 40)
                content_lines.append("")
        
        # 章节
        chapter_nums = sorted([n for n in chapters.keys() if start_chapter <= n <= end_chapter])
        
        for i, num in enumerate(chapter_nums):
            chapter = chapters[num]
            
            # 章节标题
            if include_title:
                chapter_title = chapter.get('chapter_title', f'第{num}章')
                if format_type == 'md':
                    content_lines.append(f"## {chapter_title}")
                    content_lines.append("")
                else:
                    content_lines.append(chapter_title)
                    content_lines.append("-" * len(chapter_title))
                    content_lines.append("")
            
            # 章节内容
            chapter_content = chapter.get('content', '')
            content_lines.append(chapter_content)
            
            # 分隔线
            if add_separator and i < len(chapter_nums) - 1:
                content_lines.append("")
                if format_type == 'md':
                    content_lines.append("---")
                else:
                    content_lines.append("*" * 20)
                content_lines.append("")
        
        # 构建响应
        full_content = "\n".join(content_lines)
        
        # 文件扩展名
        ext = 'md' if format_type == 'md' else 'txt'
        filename = f"{title}_正文.{ext}"
        
        # 🔥 修复：对中文文件名进行URL编码，避免HTTP头编码错误
        from urllib.parse import quote
        encoded_filename = quote(filename.encode('utf-8'))
        
        response = make_response(full_content)
        response.headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{encoded_filename}"
        response.headers["Content-Type"] = "text/plain; charset=utf-8"
        return response
        
    except Exception as e:
        print(f"导出正文失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
