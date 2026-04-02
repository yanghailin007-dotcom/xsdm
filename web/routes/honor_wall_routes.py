"""
荣誉墙API路由
"""
from flask import Blueprint, request, jsonify, session
from web.models.honor_wall_model import honor_wall_model

honor_wall_bp = Blueprint('honor_wall', __name__, url_prefix='/api/honor-wall')


@honor_wall_bp.route('/list', methods=['GET'])
def get_honor_wall_list():
    """获取荣誉墙列表"""
    try:
        # 参数
        platform = request.args.get('platform', 'all')
        sort_by = request.args.get('sort', 'likes')  # likes, newest, word_count
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 10))
        search = request.args.get('search', '')
        
        # 获取列表
        result = honor_wall_model.list_entries(
            platform=platform,
            sort_by=sort_by,
            page=page,
            per_page=per_page,
            search=search
        )
        
        # 获取当前用户点赞状态
        current_user_id = session.get('user_id')
        if current_user_id and result['entries']:
            for entry in result['entries']:
                entry['is_liked'] = honor_wall_model.is_liked(entry['id'], current_user_id)
        else:
            for entry in result['entries']:
                entry['is_liked'] = False
        
        return jsonify({
            'success': True,
            'data': result['entries'],
            'total': result['total'],
            'pages': result['pages'],
            'current_page': result['page']
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@honor_wall_bp.route('/share', methods=['POST'])
def share_book():
    """分享作品到荣誉墙"""
    try:
        # 检查登录
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        
        user_name = session.get('username', '匿名用户')
        
        # 获取参数
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': '参数错误'}), 400
        
        book_title = data.get('book_title', '').strip()
        platform = data.get('platform', '').strip()
        platform_url = data.get('platform_url', '').strip()
        book_intro = data.get('book_intro', '').strip()
        word_count = int(data.get('word_count', 0))
        
        # 验证必填字段
        if not book_title or not platform or not platform_url:
            return jsonify({'success': False, 'error': '书名、平台、链接为必填项'}), 400
        
        # 验证平台URL
        if not honor_wall_model.validate_platform_url(platform, platform_url):
            return jsonify({'success': False, 'error': '平台链接格式不正确'}), 400
        
        # 创建分享
        result = honor_wall_model.create_entry(
            user_id=user_id,
            user_name=user_name,
            book_title=book_title,
            platform=platform,
            platform_url=platform_url,
            book_intro=book_intro,
            word_count=word_count
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': '分享成功',
                'data': {'entry_id': result['entry_id']},
                'remaining_shares': result['remaining_shares']
            })
        else:
            return jsonify({'success': False, 'error': result.get('error', '分享失败')}), 400
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@honor_wall_bp.route('/<int:entry_id>/like', methods=['POST'])
def like_entry(entry_id):
    """点赞/取消点赞"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        
        # 检查作品是否存在
        entry = honor_wall_model.get_entry(entry_id)
        if not entry:
            return jsonify({'success': False, 'error': '作品不存在'}), 404
        
        # 切换点赞
        result = honor_wall_model.toggle_like(entry_id, user_id)
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@honor_wall_bp.route('/my-shares', methods=['GET'])
def get_my_shares():
    """获取我的分享"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        
        result = honor_wall_model.get_my_shares(user_id)
        
        return jsonify({
            'success': True,
            'data': result['entries'],
            'used': result['used'],
            'max': result['max'],
            'remaining': result['remaining']
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@honor_wall_bp.route('/<int:entry_id>', methods=['DELETE'])
def delete_share(entry_id):
    """删除分享"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        
        result = honor_wall_model.delete_entry(entry_id, user_id)
        
        if result['success']:
            return jsonify({'success': True, 'message': '删除成功'})
        else:
            return jsonify({'success': False, 'error': result.get('error', '删除失败')}), 400
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500


@honor_wall_bp.route('/platforms', methods=['GET'])
def get_platforms():
    """获取支持的平台列表"""
    platforms = [
        {'id': 'fanqie', 'name': '番茄小说', 'domain': 'fanqienovel.com'},
        {'id': 'qidian', 'name': '起点读书', 'domain': 'qidian.com'},
        {'id': 'qq_read', 'name': 'QQ阅读', 'domain': 'yuewen.com'},
        {'id': 'jinjiang', 'name': '晋江文学', 'domain': 'jjwxc.net'}
    ]
    return jsonify({'success': True, 'data': platforms})


@honor_wall_bp.route('/stats', methods=['GET'])
def get_stats():
    """获取荣誉墙统计数据"""
    try:
        stats = honor_wall_model.get_stats()
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500
