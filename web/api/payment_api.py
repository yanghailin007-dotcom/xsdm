"""
支付系统API - 易支付（YiiPay）接入
提供充值、订单查询、回调处理等功能
"""
import hashlib
import json
import time
import uuid
import yaml
from flask import Blueprint, request, jsonify, session, redirect
from functools import wraps
from web.models.point_model import point_model
from web.web_config import logger

payment_api = Blueprint('payment_api', __name__, url_prefix='/api/payment')

# 加载支付配置
def load_payment_config():
    """加载支付配置"""
    try:
        with open('config/payment.yaml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 从环境变量覆盖敏感配置
        config['yipay']['merchant_id'] = os.environ.get('YIPAY_MERCHANT_ID', config['yipay']['merchant_id'])
        config['yipay']['merchant_key'] = os.environ.get('YIPAY_MERCHANT_KEY', config['yipay']['merchant_key'])
        config['yipay']['api_url'] = os.environ.get('YIPAY_API_URL', config['yipay']['api_url'])
        
        return config
    except Exception as e:
        logger.error(f"加载支付配置失败: {e}")
        return {'enabled': False}

# 登录验证装饰器
def login_required_api(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in') and 'user_id' not in session:
            return jsonify({'success': False, 'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function


def generate_sign(params, key):
    """
    生成易支付签名
    按照易支付规范：参数按ASCII排序后拼接成字符串，最后加上key进行MD5加密
    """
    # 过滤空值和sign参数
    filtered_params = {k: v for k, v in params.items() if v is not None and k != 'sign'}
    
    # 按ASCII排序
    sorted_params = sorted(filtered_params.items())
    
    # 拼接成字符串
    sign_str = '&'.join([f"{k}={v}" for k, v in sorted_params])
    
    # 加上key
    sign_str += f"&key={key}"
    
    # MD5加密并转大写
    return hashlib.md5(sign_str.encode('utf-8')).hexdigest().upper()


def verify_sign(params, key):
    """验证易支付回调签名"""
    sign = params.get('sign', '')
    if not sign:
        return False
    
    calculated_sign = generate_sign(params, key)
    return sign.upper() == calculated_sign.upper()


# ==================== 充值API ====================

@payment_api.route('/config', methods=['GET'])
@login_required_api
def get_payment_config():
    """获取支付配置和充值选项"""
    config = load_payment_config()
    
    if not config.get('enabled'):
        return jsonify({
            'success': False,
            'error': '支付功能暂未开启'
        }), 400
    
    return jsonify({
        'success': True,
        'data': {
            'enabled': True,
            'exchange_rate': config.get('exchange_rate', 1),
            'recharge_options': config.get('recharge_options', []),
            'min_amount': config.get('min_amount', 1),
            'max_amount': config.get('max_amount', 5000)
        }
    })


@payment_api.route('/create_order', methods=['POST'])
@login_required_api
def create_order():
    """创建充值订单"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': '用户信息不完整'}), 401
    
    config = load_payment_config()
    if not config.get('enabled'):
        return jsonify({'success': False, 'error': '支付功能暂未开启'}), 400
    
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': '请求参数错误'}), 400
    
    amount = data.get('amount', 0)
    
    # 验证金额
    min_amount = config.get('min_amount', 1)
    max_amount = config.get('max_amount', 5000)
    
    if not isinstance(amount, (int, float)) or amount < min_amount:
        return jsonify({
            'success': False, 
            'error': f'充值金额不能低于{min_amount}元'
        }), 400
    
    if amount > max_amount:
        return jsonify({
            'success': False, 
            'error': f'充值金额不能超过{max_amount}元'
        }), 400
    
    # 计算赠送点数
    bonus = 0
    for option in config.get('recharge_options', []):
        if option['amount'] == amount:
            bonus = option.get('bonus', 0)
            break
    
    total_points = amount + bonus
    
    # 生成订单号
    order_id = f"PAY{int(time.time())}{user_id}{uuid.uuid4().hex[:8]}"
    
    # 保存订单到数据库
    try:
        from web.models import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO payment_orders 
            (order_id, user_id, amount, bonus, total_points, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (order_id, user_id, amount, bonus, total_points, 'pending', int(time.time())))
        
        conn.commit()
        conn.close()
        
        logger.info(f"创建充值订单: order_id={order_id}, user_id={user_id}, amount={amount}")
        
        return jsonify({
            'success': True,
            'data': {
                'order_id': order_id,
                'amount': amount,
                'bonus': bonus,
                'total_points': total_points,
                'pay_url': f"/api/payment/pay?order_id={order_id}"
            }
        })
        
    except Exception as e:
        logger.error(f"创建订单失败: {e}")
        return jsonify({'success': False, 'error': '创建订单失败，请稍后重试'}), 500


@payment_api.route('/pay', methods=['GET'])
@login_required_api
def go_pay():
    """跳转到支付页面"""
    user_id = session.get('user_id')
    order_id = request.args.get('order_id')
    
    if not order_id:
        return jsonify({'success': False, 'error': '订单号不能为空'}), 400
    
    config = load_payment_config()
    if not config.get('enabled'):
        return jsonify({'success': False, 'error': '支付功能暂未开启'}), 400
    
    try:
        # 查询订单
        from web.models import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM payment_orders 
            WHERE order_id = ? AND user_id = ?
        ''', (order_id, user_id))
        
        order = cursor.fetchone()
        conn.close()
        
        if not order:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        
        if order['status'] != 'pending':
            return jsonify({'success': False, 'error': '订单状态异常'}), 400
        
        # 构建易支付请求参数
        pay_params = {
            'pid': config['yipay']['merchant_id'],
            'type': config['yipay']['pay_type'],
            'out_trade_no': order_id,
            'notify_url': request.host_url.rstrip('/') + config['yipay']['notify_url'],
            'return_url': request.host_url.rstrip('/') + config['yipay']['return_url'],
            'name': f"充值{order['amount']}点",
            'money': str(order['amount']),
            'param': str(user_id)  # 透传参数，回调时原样返回
        }
        
        # 生成签名
        pay_params['sign'] = generate_sign(pay_params, config['yipay']['merchant_key'])
        pay_params['sign_type'] = 'MD5'
        
        # 构建支付URL
        pay_url = config['yipay']['api_url'] + '/submit.php'
        
        # 返回表单数据，前端自动提交
        return jsonify({
            'success': True,
            'data': {
                'pay_url': pay_url,
                'pay_params': pay_params,
                'method': 'POST'
            }
        })
        
    except Exception as e:
        logger.error(f"构建支付请求失败: {e}")
        return jsonify({'success': False, 'error': '支付请求失败'}), 500


@payment_api.route('/notify', methods=['POST'])
def payment_notify():
    """支付异步回调"""
    config = load_payment_config()
    if not config.get('enabled'):
        return 'fail', 400
    
    # 获取回调参数
    params = request.form.to_dict() if request.form else request.json
    if not params:
        return 'fail', 400
    
    logger.info(f"收到支付回调: {params}")
    
    # 验证签名
    if not verify_sign(params, config['yipay']['merchant_key']):
        logger.error("支付回调签名验证失败")
        return 'fail', 400
    
    # 获取订单信息
    order_id = params.get('out_trade_no')
    trade_no = params.get('trade_no')  # 易支付订单号
    trade_status = params.get('trade_status')
    
    if trade_status != 'TRADE_SUCCESS':
        logger.warning(f"支付未完成: {trade_status}")
        return 'success'  # 返回success避免重复通知
    
    try:
        from web.models import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 查询订单
        cursor.execute('SELECT * FROM payment_orders WHERE order_id = ?', (order_id,))
        order = cursor.fetchone()
        
        if not order:
            logger.error(f"回调订单不存在: {order_id}")
            return 'fail', 404
        
        if order['status'] == 'completed':
            logger.info(f"订单已处理: {order_id}")
            return 'success'
        
        if order['status'] != 'pending':
            logger.warning(f"订单状态异常: {order_id}, status={order['status']}")
            return 'fail', 400
        
        user_id = order['user_id']
        total_points = order['total_points']
        
        # 更新订单状态
        cursor.execute('''
            UPDATE payment_orders 
            SET status = ?, trade_no = ?, paid_at = ?
            WHERE order_id = ?
        ''', ('completed', trade_no, int(time.time()), order_id))
        
        conn.commit()
        conn.close()
        
        # 发放点数
        result = point_model.add_points(
            user_id=user_id,
            amount=total_points,
            source='recharge',
            description=f'支付宝充值: ¥{order["amount"]}，获得{total_points}点'
        )
        
        if result['success']:
            logger.info(f"充值成功: order_id={order_id}, user_id={user_id}, points={total_points}")
            return 'success'
        else:
            logger.error(f"发放点数失败: {result}")
            return 'fail', 500
            
    except Exception as e:
        logger.error(f"处理支付回调失败: {e}")
        return 'fail', 500


@payment_api.route('/query', methods=['GET'])
@login_required_api
def query_order():
    """查询订单状态"""
    user_id = session.get('user_id')
    order_id = request.args.get('order_id')
    
    if not order_id:
        return jsonify({'success': False, 'error': '订单号不能为空'}), 400
    
    try:
        from web.models import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM payment_orders 
            WHERE order_id = ? AND user_id = ?
        ''', (order_id, user_id))
        
        order = cursor.fetchone()
        conn.close()
        
        if not order:
            return jsonify({'success': False, 'error': '订单不存在'}), 404
        
        return jsonify({
            'success': True,
            'data': {
                'order_id': order['order_id'],
                'amount': order['amount'],
                'bonus': order['bonus'],
                'total_points': order['total_points'],
                'status': order['status'],
                'created_at': order['created_at'],
                'paid_at': order['paid_at']
            }
        })
        
    except Exception as e:
        logger.error(f"查询订单失败: {e}")
        return jsonify({'success': False, 'error': '查询失败'}), 500


@payment_api.route('/orders', methods=['GET'])
@login_required_api
def get_order_list():
    """获取充值记录"""
    user_id = session.get('user_id')
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    try:
        from web.models import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        offset = (page - 1) * limit
        
        # 查询总数
        cursor.execute(
            'SELECT COUNT(*) as total FROM payment_orders WHERE user_id = ?',
            (user_id,)
        )
        total = cursor.fetchone()['total']
        
        # 查询记录
        cursor.execute('''
            SELECT * FROM payment_orders 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (user_id, limit, offset))
        
        orders = cursor.fetchall()
        conn.close()
        
        return jsonify({
            'success': True,
            'data': {
                'total': total,
                'page': page,
                'limit': limit,
                'orders': [dict(order) for order in orders]
            }
        })
        
    except Exception as e:
        logger.error(f"获取充值记录失败: {e}")
        return jsonify({'success': False, 'error': '获取失败'}), 500
